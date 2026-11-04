# Aurora storage and PBS charging account

The user's required target is Aurora, with PBS charging account
`BioReason-Aurora-Test`. On 2026-11-04 UTC the user changed billing from EpiCalib
after the live allocation check showed EpiCalib had expired on 2026-11-01.
All workflow software, environments, databases, inputs, temporary files, caches,
logs and run directories belong under `/lus/flare/projects/BioReason-Aurora-Test`.
The existing personal workspace is `/lus/flare/projects/BioReason-Aurora-Test/chian`;
put disposable execution output beneath its `runs/` directory. Billing and
storage remain independent configuration fields even when their project names match.

The only workflow file allowed in Aurora home is the small directory index
`/home/chian/WORKSPACE_DIRECTORY.md`. Do not put run folders, environments,
output, caches, temporary files or backups in home.

The caller's `workspace` and `account` are independent configuration fields.
The practical assignment supplies its own `workspace` within the configured
workspace. Selected file operations and persistent `cwd` must remain within
that assignment workspace. Configure both fields explicitly to satisfy the
requirements above; do not silently change a conflicting account or workspace.

PBS submission uses `configuration.account`; assignment `constraints.account`
or `constraints.allowed_accounts`, when supplied, must agree. Selected `queue`
and `resources` are separately checked against the assignment's corresponding
constraints and `allocation`. A storage location does not select an account,
and an account does not change the workspace. A conflict remains explicit
feedback rather than an implicit configuration change.

The initial and working contexts retain explicit `cwd` and `environment`.
Preparation commands do not replace the requested job's original environment.
Keep chosen working, temporary, cache and output paths consistent with the
actual assignment and operation contracts. If module loading changes cache or
user-base variables, restore their project locations before an operation writes.

An `inventory_snapshot` identifies supplied preparation records and their
observed provenance. Its hash identifies catalog bytes, not current file
existence, runtime usability, quota or allocation balance. Current filesystem,
scheduler and account observations retain their own times and native sources;
they do not rewrite the original job's account or preparation record.

The 2026-10-22 manual run charged `BioReason-Aurora-Test`. Preserve that historical
receipt and any records from the intervening EpiCalib instruction. New jobs use
`-A BioReason-Aurora-Test`; current instructions do not relabel earlier allocations.
