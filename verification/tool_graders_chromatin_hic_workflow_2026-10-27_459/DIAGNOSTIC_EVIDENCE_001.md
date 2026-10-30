# Retained native signal and controlled schema checks

`check001` failed during administrative bootstrap because `-S` hid the
infrastructure environment's jsonschema dependency. No handle or scientific
job was created. Its source snapshot and `ADMINISTRATIVE_FAILURE.json` remain.

`check002` is an actual terminal, quiescent native returncode **-11**, not a
timeout. The original handle is `check002/handle.json`, unit
`gene-local-job-23723a75fffe4892a5978fe2152dbc6b.service`. The retained receipt
reports122.527301834 seconds, unchanged frozen source/interpreter pins,
56,320,000 observed scratch bytes,20GiB RAM,4GiB scratch, zero swap and no wall
limit. Systemd reports226,115,584 bytes peak memory and zero swap. The exact
kernel time-window query returned no matching entries. This supplies no kernel
crash location.

The actual HIC producer returned0 and retained complete p0/p1 extractions.
The Workflow database retains four model calls and four selected actions;
the local `practical.job.start` and its parent launch_local commission have
recorded results. One local observation and one form are retained. The
scientific and root commissions have no result, and no results child was
commissioned. The actual receipt establishes handoff credit7; later unrecorded
credit is not inferred. `FAILURE_EVIDENCE.json` records these exact durable
counts and the original observation.

The30/60/90/120-second periodic stack samples are retained in full. The last
sample ends mid-frame while describing `referencing._core.Resource.__init__`.
Earlier samples include schema validation and practical completion/report
validation. A sampled function does **not** identify the crashing function.
451 independently observed another terminal-11 full Workflow run ending
mid-periodic-frame before its native producer started. These observations
motivate a periodic-instrumentation hypothesis; they do not prove it.

The paired diagnostic uses exactly the four retained host schemas, raw
provider responses and authoritative selected actions, and the real practical
assignment/baseline/start receipt. The input SHA256 is
`2fcc2bbd297cb690778908b6433b148d68b6361e1cdb75054e426658035b71ac`.
Both arms import the unchanged `check002/source_snapshot` application.
They call actual provider-schema generation, current/historical decoder
comparison with the recorded selection, provider and host schema validators,
practical assignment/receipt validation and `project_practical_credit`.
They create no Workflow action, observation, native job or scientific result.

Both arms enable separate fatal-fault capture. Their only behavioral difference
is `dump_traceback_later(30, repeat=True, exit=False)` enabled or disabled.
All runs use the same ordinary bounded local lifecycle and retain original
handles/receipts/pins. The first pair completed16 iterations in about10seconds;
it did not reach a periodic dump and is not instrumentation evidence.

The longer pair completed256 iterations in each arm, including1,024 provider
schema validations and1,024 corresponding host validations per arm. Each
practical projection retained actual original credit7 and baseline0.

| Attempt | Native result | Iterations | Elapsed diagnostic seconds | Periodic dumps |
| --- | --- | --- | --- | --- |
| diagnostic002_periodic | 0 | 256 | 162.28714694804512 | 5 |
| diagnostic002_no_periodic | 0 | 256 | 163.8016113260528 | 0 |

Both have unchanged pins and empty fatal-fault logs. The isolated inputs pass;
the full-context SIGSEGV was not reproduced and its cause remains unproven.
No production validator, scientific input, credit rule or resource allocation
was changed. Subsequent controlled full verification must preserve the original
failed attempt and distinguish its source snapshot from other runs.
