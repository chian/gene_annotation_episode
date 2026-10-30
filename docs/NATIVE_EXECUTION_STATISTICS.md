# Completion recording and recovery

`execution_recording.py` connects durable native execution receipts to the
restricted `RunHistory` interface. It imports no scientific Store, model,
episode runtime, task-credit projector or yield estimator. The global boundary
still admits only `ExecutionClass` and `RunStatistic` values.

## Ownership and configuration

The caller may supply a `HomologyStatistics` binding to `HomologyEpisodes`.
It names an explicit shared history path, configured resource identity and known
reference record/residue counts. Unknown corpus sizes remain null. No default
history is created in an individual run workspace. The caller initializes the
shared history; an unavailable/missing/unrelated database is not silently adopted.
The binding and the registry's resource settings are frozen in the run manifest.
Episodes cannot override them in selected tool arguments.

The class of a homology execution binds actual binary and database digests,
native-default search options, selected CPU allocation, query length, known
corpus sizes, effective memory/scratch/wall policy and
`systemd_service_wall_seconds`. Query identities and sequences are absent from
the global class. Different query sequences of the same size can share this
exact execution class; different databases, binaries, CPU or policies cannot
silently share its statistics. This is descriptive compatibility grouping,
not a calibrated general runtime model.
The parameter digest also binds the native lifecycle version so a changed
dispatch/timing protocol does not silently pool durations from an older one.

Homology reservations carry a `not_started` statistical context and no execution
timestamp. Just before their actual dispatch, `NativeStatistics.capture` reads the caller's
current resource-condition reference. That context is written into the durable
native handle before the command is released. If the history is unavailable,
the condition remains explicitly unknown. Reporting an outage later cannot
relabel this attempt. A captured unavailable-service condition does not prevent
the launch episode's selected execution.

Thus a process interruption while a reservation is offline cannot accumulate
fake runtime or attach an old reservation-time service condition to a later
dispatch. A completed attempt still retains its original captured condition.

## Completion path

The existing native worker's systemd completion hook first writes its actual
service end receipt. When statistics are configured, it then invokes
`publish_native_statistics` using the retained native handle. This does not
depend on the workflow, launch child or monitoring child remaining alive.
It starts no new scientific work and makes no controller observation.

The exporter reads the native/service receipts, records the observed outcome
and computes elapsed time from their original monotonic timestamps when their
boot identities match. Missing end evidence produces no completed sample.
Unknown duration stays null; negative chronology is an invalid receipt, not a
value clamped to zero. Native exit codes are never fabricated. An observed
resource failure is grouped separately from a successful execution. A missing
or failed native receipt is the same execution failure recognized by collection.

The physical attempt hash binds unit, boot and start identity. The source hash
binds original native-handle, native-result and service-end bytes. Another actual
execution has another attempt identity; another poll/export of the same attempt
does not. A conflicting receipt cannot overwrite an existing measurement.
The observation timestamp is the original completion time, not export/retry time.
No source text, match, annotation, finding, recommendation, credit or yield history
is serialized into the global measurement.

## Independent failure and recovery

Statistics transport is nonblocking on SQLite lock contention. This is an
infrastructure-write policy, not a native work timeout or episode stop rule.
A missing, locked or invalid history produces a job-owned export disposition;
the original native results and success/failure meaning survive. A late export
uses the original condition and timestamps. It does not rerun the job or revise
completed-child credit/history.

The completion hook and recovery use the same exporter. A per-attempt file lock
coordinates concurrent exporters; `RunHistory` independently deduplicates the
physical attempt. The native handle names the standard export disposition file.
If the native receipt cannot be read, a separate basic recovery diagnostic can
be retained beside it; that diagnostic is not authoritative execution state or
global history. If the filesystem also prevents diagnostic persistence, the
recovery caller receives that failure explicitly.

The shared runtime retries retained exports at startup and after selected job
operations when the optional binding is enabled. Startup consumes them as a
stream and retains only disposition counts. Closed native logs remain on disk.
An assigned child's tool result may include its export disposition; no extra
parent report field, form composer or credit projection follows. The episode
expectation interface captures later global snapshots normally, preserving the
snapshot that actually informed each earlier decision.

This integration records selected homology-search attempts. Results-parser jobs
and other native phases are not silently relabeled as homology searches. The two
older empirical probe records retain their original duration meaning; they are
not rewritten or pooled into the new service-duration class.

## Verification scope

Actual small native-service checks cover completion after launcher exit,
independent runs sharing an exact class, immutable earlier snapshots, repeated
export, missing/locked history, late outage notices, receipt conflicts and
preserved native outcomes. They use explicitly labeled engineering programs,
not biological evidence or the production shared history.

The job-role integration check runs actual one-reference phmmer and the bounded
parser through the shared method_loop with scripted decisions and fixture scores.
Monitoring sees no completed-run sample while execution is running. A later
results episode receives the actual completed duration through its expectation
context. The parent receives its chosen forms, not an export/statistics dump.
Interrupted-job recovery exports a missing measurement while preserving prior
raw scores and completed-action counts. No configured model, full-corpus rerun
or completed scientific annotation is established by these checks.
