# Native AppService monitoring verification

All 112 currently collected cases have passing results across the recorded
runs: 64 native-monitor cases, 27 monitor-port cases, six API-recovery cases and
15 execution-progress cases. [SUMMARY.json](SUMMARY.json) records their exact
node IDs, coverage and owned-source hashes.

The original combined run passed 40 cases before an incorrect test fixture
declared an 11-byte log at offset 7 with observed size 17. The fixture was
corrected to end/size 18 and bounded start 15; production code was unchanged.
The continuation then passed the corrected case and every remaining case
(`70 passed in 302.79s`). After adding original C8 snapshot/reference and
selection-signature verification, all seven affected dependency cases passed
(`7 passed, 57 deselected in 96.71s`), including two new corruption cases.
The initial failed attempt remains in [tests.log](tests.log); the successful
continuation and focused run remain in [followup.tests.log](followup.tests.log)
and [dependency.tests.log](dependency.tests.log). Each has its exact command and
timing/result JSON alongside it.

The native tests create a real Store, journal, saved launch/handoff and monitor
commissions with the production host fixtures. They call the actual
APIServiceExecution, BVBRCAppServiceService and controlled native client. The
consumer cases also call MonitorEpisodes, WorkflowServices, ProgressProvider,
ExecutionProgressProvider and retained `progress.log` reads.

Coverage includes:

- Exact original task, saved action, native choice, context and assignment;
  original parent possession before commission; recursive same-target monitors;
  a different dependency obtained through prior completed C8 observation or an
  explicitly requested typed form; source/submission identity and receipt cutoff;
  rejection of descriptor visibility, rewritten C8 data and late delivery.
- Separate status and log calls; saved-response and reopened-executor replay;
  interruption before issue, after possible issue, after response and during
  later C8 publication; structured AcquisitionError data and partial raw bytes.
- Log-only unknown execution state, exact native timing strings and unknown
  timezone, no raw payload in nested native projection, actual saved field
  restrictions, caller role/byte limits, nonzero original offsets, empty byte
  windows and invalid UTF-8. A configured zero-byte limit remains invalid under
  the existing policy. The nonzero-offset case adjusts the provider input after
  an actual native call; it does not claim remote range support.
- Existing omitted-keyword behavior and unchanged monitoring-information credit
  for repeated status facts. The helpers create no extra controller observations.

No live API or HPC call was made. The native-monitor fixture blocks socket and
urllib transport. These tests do not run a configured model or the complete
shared method_loop, and do not establish its final one-action observation
accounting. The unrelated recursive-monitor `episode.history` failure was not
changed or rerun.

Ownership is limited to the new native-monitor module and tests,
APIServiceExecution.observe_target, and the approved AppService-only selection
and log-window provider changes. [verified_owned_slices.json](verified_owned_slices.json)
retains the exact shared-file slices. Root independently corrected submission
receipt parameter precedence during these runs; this report makes no claim
that all shared AppService sources were final when the tests imported them.
That submission-only change is outside this monitor verification scope.
