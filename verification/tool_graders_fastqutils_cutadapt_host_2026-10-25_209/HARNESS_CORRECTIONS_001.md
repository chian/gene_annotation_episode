Run 001 failed before selected execution because the new 209 test compared the
generator returned by `EpisodeReceipts.known()` directly with `[]`. The correction
materializes that iterator with `list(...)` and still requires zero initial known
records. It does not change production, imported helper assertions or custody.
The original failing source, stdout, XML, command and receipt remain in
`host_run_001`. The runner now also retains exact harness snapshots per run.

Run 002 completed the actual controlled host acquisitions and both typed
admissions, then failed at the new test's requirement-code expectation. The
older nine-field fixture uses association metadata that produces
`stage_execution_unknown`; this two-document scenario has empty metadata and
returns `producer_version_unproven` and `unknown_quality_encoding`. All actual
stage observations remain unknown and were checked separately before that
assertion. The workload requires typed requirements, not the older fixture's
specific extra diagnostic.

Only that fixture-specific code is removed from the new 209 assertion. The
production sources, imported helper assertions, selected fields, numerical
expectations, source checks and explicit unknown stage checks are unchanged.
Run 002's original failed source snapshot, complete Store, host receipts, stdout,
XML and exit-1 terminal receipt remain unchanged. Root instructed continuation
from those saved publications/admissions with execution disabled, so no new
prepare, submission, status or download is performed to obtain a passing result.
The saved-evidence verification is a separate result and does not relabel the
original full-path run as passing.

Saved-check runner 003 stopped in preflight before opening state or collecting a
test: its glob included pytest's `current` directory symlink and the same real
directory. The runner now deduplicates resolved paths. Both the failed runner
source and an explicit preflight receipt remain in `host_saved_003`; the original
state and its symlink are unchanged. No acquisition was repeated.
