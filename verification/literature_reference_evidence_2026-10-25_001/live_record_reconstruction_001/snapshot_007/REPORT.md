# Saved live-record reconstruction audit

Run: `run_2d881b3438f247d59d79e6f00edb3102`.

Status: **passed_with_pending_boundaries**. Copied 27 immutable artifacts from a consistent read-only SQLite backup.
Verified 4 actual selected population sheets, their immutable requests/payloads, requested typed saved-cell projections and owning-episode receipts.
Actual report attempts: 5. Actual admitted parent subsets: 1.

| Episode | State | Action rows | Observation rows | Accounting |
|---|---|---:|---:|---|
| literature | active | 17 | 16 | {'completed_observed': 16, 'failed_attempt_no_observation': 1} |
| annotation | active | 14 | 12 | {'completed_observed': 12, 'pending_selected_work': 2} |
| literature | yielded | 60 | 58 | {'completed_observed': 58, 'failed_attempt_no_observation': 2} |
| literature | yielded | 60 | 58 | {'completed_observed': 58, 'failed_attempt_no_observation': 2} |
| literature | yielded | 59 | 58 | {'completed_observed': 58, 'failed_attempt_no_observation': 1} |
| literature | yielded | 62 | 58 | {'completed_observed': 58, 'failed_attempt_no_observation': 4} |
| literature | yielded | 62 | 58 | {'completed_observed': 58, 'failed_attempt_no_observation': 4} |

Projection used the pinned actual Store/repository in a fresh offline audit process, followed by a second Store close/reopen. Population, parsing, calculators, model entrypoints and receipt writes were disabled. Projection ran with SQL query-only and a private-table/mutation authorizer; saved public row hashes stayed equal. No live Store was opened and no delivery or observation was created.

Pending:

- Active episode work/closure remains pending; this audit does not force continuation or closure.

Limits:

- Consistent SQLite backup and immutable artifact custody establish this snapshot only; the live run can advance afterwards.
- Requested saved-cell diagnostic projection is not an actual child closure, receipt admission, or parent delivery.
- Repository reopen in an offline process does not establish an actual host restart or full workflow reconstruction/resume.
- This engineering audit does not assess primary-source science, experimental validity, scoring suitability, final credit, or scientific completion.
- SQLite backup includes database tables without interpreting private model-call contents; those tables are not queried by the audit.
