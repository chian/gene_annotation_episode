# Protein result receipt implementation, 406

2026-10-27. This packet owns only `protein_structure_result_receipts.py`, its
focused test file and this new verification directory. The original immutable
goal and all sixteen design principles govern the work. Their objective and
entire principle block were reread after the first test-output examination.
The approved 403/001–003 contract and additive 403/004 lifecycle clarification
are consumed without modifying them. The integrated tool count remains112/308.

## Implemented boundary

- Exact closed intent, handoff-proof, body, publication, receipt, accounting and
  qualified-file TypedDicts; opaque lock-bound `ProteinResultAction`.
- Inert constructor and pure action path derivation; lazy397 returns access.
- Safe component-by-component directory/file opening, immutable canonical
  controls and one exclusive OS lock for the complete selected action. Blocking
  acquisition runs in `asyncio.to_thread`, shielded and drained before descriptor
  release after cancellation. Every action-taking method checks live instance,
  intent, directory and lock-file identity. No transaction crosses lock await.
- Private staged replay accepts an original pending runtime row. Completed
  history instead requires the exact completed collect outcome and equality of
  every immutable control copy. A committed runtime outcome with missing private
  receipt cannot restart acquisition. Status and pending actions grant nothing.
- Fresh original commission/full-request/scope/target proof through397; copied
  practical source/body/assignment metadata and the original recorded start
  action; compact capture/bundle/worker/source/reference/publication proof.
- Metadata-only historical checks use Store identities and captured canonical
  control digests. They do not open native results, sheets, maps, components,
  selected tables or vanished practical handoff artifacts. Saved work checks
  original custody recursively and freshly proves actual descriptor receipt
  through397. Per-call cycle state is released after each read.
- Classification reads ordinary protein provenance and published runtime
  membership across runs. It creates no membership table/index and grants no
  access. Known membership is reconstructed from body metadata; remaining
  lifecycle members are original recorded metadata as specified in403/004.

No native execution, scientific parsing, calculation, result publication,
scoring/credit formula, model prompt, literature path or W05 aggregation is
implemented in this module.407 owns the host and initial scientific byte
qualification. Root owns all shared binding, return/credit/endpoint wiring and
the complete receiving-episode test.

## Verification qualification

`fixture_helpers.py` uses actual Store, Journal, parent commissions, receipt
inheritance, PracticalState, PracticalReceiptInformation and397 authentication.
Its `injected_handoff` and `injected_publication` explicitly inject compact
native/worker qualification metadata for receipt mechanism tests. They are not
evidence of a live scientific job, a bounded result worker or method_loop's
completed-action observation. The optional `live()` helper uses the actual
selected PracticalResourceEpisodes launch and original native handle;407 uses
that path in its independently owned host tests.

The focused tests cover private pending replay, exact runtime outcomes,
full-context/commission tampering, compact metadata contradictions, lost control
files, complete scientific/handoff byte loss, same-source distinct collections,
foreign-run classification, pending private membership denial, symlinks,
fabricated/expired/replaced-lock actions, transaction rejection, simultaneous
callers, and cancellation/repeated cancellation while waiting for the OS lock.

All pytest execution uses `run_bounded.py` and existing local_jobs with20GiB RAM,
4GiB scratch, zero swap and no wall-time budget. Every attempt retains an
immutable executed source snapshot, before/after hashes, exact command,
stdout/stderr and actual native receipt. Checkout drift is separately recorded
because other approved lanes share the workspace; it cannot alter executed
snapshot bytes.

check001:57 passed,1 failed in742.15s. The sole failure was the concurrency
test's arbitrary five-second watchdog expiring during publication validation.
Its cancellation still drained the waiting lock acquisition. The test watchdog
was removed; the event-loop responsiveness assertion and exact same-receipt/
single-qualification assertions remain. The failed run is retained unchanged.
Several proof checks were added after that snapshot, so check001 is not claimed
as final-source verification. check002 is the current full-source rerun; its
result will be recorded additively after completion.

This supporting receipt module does not establish full tool acceptance,
configured-model science, complete episode communication or operational-credit
correctness by itself.
