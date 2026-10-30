# Actual run evidence and limits

The final checker run is `snapshot_002/receipt.json`, with its concise
`snapshot_002/REPORT.md` and exact command in `README.md`.

The read transaction/backup ran from **2026-10-26 02:35:41.832148 UTC** to
**02:35:42.231993 UTC**, against actual run
`run_2d881b3438f247d59d79e6f00edb3102`. It captured 19 registered immutable
artifacts. All **518** pinned manifest files matched before and after the work;
the manifest SHA-256 is
`4e811a570f71e046ad04a8bb112b96bb2074ad2019b7c95a06a161c9c16613f7`.

The checker proved actual selected `literature.ratio.populate` decisions **8, 9,
10 and 11** each bind to their saved request, operation signature, runtime action
outcome, content-addressed sheet source, unchanged immutable payload, owning
episode receipt, and four requested typed cell projections. All **16** projected
cells copied the saved values/status/units/origin/missingness/candidate sets;
unreceived-sheet projection was rejected. The receipt includes exact sheet and
payload identities. This is structural verification of saved results, without
scientific reassessment.

| Episode | Action rows | Observations | Explanation |
|---|---:|---:|---|
| annotation/root | 4 | 2 | Two completed waits observed; pending child commission and pending selected wait have no observations. |
| literature/child_2 | 56 | 52 | 52 completed own actions observed exactly once; four failed attempts have no completed credit or observations. |

The actual report-attempt count is **zero** and the admitted parent cell-subset
count is **zero**. Both episodes were active. Actual child closure, parent typed
delivery and parent subset retention remain **pending/unverified**. No delivery
was fabricated and no completion was forced. The source of the four failed
attempts and their feedback codes is preserved in the per-action receipt rows.

A fresh offline audit process opened the owned backup with the actual pinned
Store/repository; a second Store close/reopen preserved payloads and public row
hashes. During projection, acquisition/population/parsing/calculation/model and
delivery entrypoints were disabled; SQL query-only, mutation/private-table
authorizer, saved-artifact allowlist and offline host-call guard were active.
No disabled entrypoint or denied SQL operation was attempted. This proves saved
repository result reuse; **an actual host restart and full workflow resume were
not established**.

The unchanged saved model configuration uses `gpt-6-sol` with medium reasoning
for decisions/child interpretation and `gpt-6-luna` with no reasoning for FAST.
The saved controller remains cost 0.001, subsample 4, window 8, alpha 0.05. The
checker copied those recorded settings and neither invoked nor refit them.

`negative_checks_001/checks.json` records three successful controlled rejection
checks: an altered owned sheet artifact, altered owned operation cells, and reuse
of an existing output directory were rejected. These tampered-copy tests are
engineering checks and are not additional actual scientific work or delivery.

All new files are confined to `live_record_reconstruction_001/`. No runtime,
immutable pin, input packet, model/controller policy or live Store was edited.
Original paper/packet bytes were not interpreted; provider files/private model
call contents were not inspected. Later live progress is outside this snapshot.
