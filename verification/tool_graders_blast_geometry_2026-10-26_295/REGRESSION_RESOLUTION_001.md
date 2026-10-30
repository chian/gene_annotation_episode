# Resolution of the expanded regression run

The original `checks_003` run is terminal: 226 passed, 15 failed and five errors.
Its original logs and native control files remain unchanged. Root recovered
that original outcome in `checks_003/RECOVERED_RECEIPT_001.json`; the recovery
did not restart or cancel the job and does not reconstruct an unavailable
end-of-run source snapshot.

The 15 failures were old test expectations: 11 called retired annotation
scoring, two selected execution tools at annotation root, and two patched a
removed CLI import. Workload 299 corrected those fixtures while retaining
numeric, source/operand, root-ownership, cancellation, action-accounting and
typed-return checks. Its final targeted run passed 34 tests, including new
current API-child cancellation/recovery checks. Production code was unchanged.

The five errors shared the pairwise Workflow's final source-provenance
assertion. Nine production files changed during the long original run. That
assertion prevented claiming verification on stable source; it did not itself
establish a numerical defect. Workload 301 copied the relevant source,
fixtures, static data and selected scientific library into an isolated
snapshot, preserved the original test and provenance assertion, and reran only
that five-case module. All five tests passed in 837.132 seconds. Acquisition
and execution hashes were stable, and all loaded project/fixture modules
resolved to the copied source.

The 301 example returned query coverage 9/15, reference coverage 3/5, three
codon-to-residue pairs and identity 3/3. It exercised the production selected
API-child, artifact association, numerical functions and requested return with
synthetic service bytes and scripted decisions. No live service or BLAST run
is claimed by that verification.

Evidence is retained in:

- `../tool_graders_blast_regressions_2026-10-26_299/DIAGNOSIS.json`,
  `REPORT.md` and `checks_003/`;
- `../tool_graders_bvbrc_pairwise_frozen_2026-10-26_301/REPORT.md`,
  `DIAGNOSIS.json`, `SOURCE_SNAPSHOT_RECEIPT.json`,
  `SOURCE_SNAPSHOT_MANIFEST.json` and
  `snapshot/verification/frozen_check_001/`.

These separate runs resolve the identified failed cases. They do not turn the
original broad run into a passing run and do not establish a frozen all-suite
pass. Earlier handoff statements that the original run was pending remain
historical records.
