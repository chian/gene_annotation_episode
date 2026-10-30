# Configured AP run: process loss observed read-only

At 2026-10-28T23:25:35.688650Z the public operator status could no longer
confirm the original process incarnation (PID 3726505, start ticks 102022369,
boot ID d53ef063-e9a7-4ae1-99ad-c64c17bdff26). `ps` and `/proc` also found no
such process. The retained terminal session identifier was unavailable to the
current tool service, so no exit code or cause was established. No private
provider output, conversation, event log or raw transport was read.

The original pinned run `run_266d996f86fb4fc491a5fac50d62cd33` remains in
database state `running` with two active episode rows. A read-only SQLite
`PRAGMA quick_check` returned `ok`. The last public status at this review has
615 action rows, 548 ordinary observations, 618 model-call rows with one
pending response, nine admitted child deliveries and nine report attempts.
The record count is not a scientific score or a final return.

`PUBLIC_TYPED_RETURN_002.json`, `PUBLIC_SUMMARY_002.json` and
`ACTUAL_IMPORTS_002.json` do not exist. `STATUS_002.json` still says `started`.
The caller's normal finalization writes those files and changes the run state;
that path did not complete. The exact cause of process disappearance remains
unknown. This is neither scientific completion nor proof of a clean yield.

The run, database, WAL, source pin, original contracts and admitted forms were
left unchanged. No restart, cancellation, settings edit, controller change,
target finding, speculative credit or new configured run was performed.
Recovery would need to preserve the original run and avoid repeating pending
selected work; it has not been attempted here. The existing source-only
progress-binding limitation remains separate from this process loss.
