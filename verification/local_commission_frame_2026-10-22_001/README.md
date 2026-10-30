# Local commission frame verification capsule

This read-only capsule preserves the isolated 123-file Python implementation,
three test files, original pyproject and baseline manifest, initial module/test
inputs, four fixed scopes, exact two-line fixture correction and both publishable
verification logs. The raw first log, caches, live state and histories are absent.

Read the [verification report](../../docs/LOCAL_COMMISSION_FRAME_VERIFICATION_2026-10-22_001.md),
[results](results.json) and [source identities](SOURCE_IDENTITIES.json).

`MANIFEST.json` lists SHA256 and byte size for every capsule member and the
external report at `../../docs/LOCAL_COMMISSION_FRAME_VERIFICATION_2026-10-22_001.md`.
The manifest excludes itself to avoid a self-hash cycle; its own SHA256 is
reported separately. All other paths are relative to this capsule directory.

The final outcome is 107 distinct passing engineering cases: 78 new component
cases and 29 original E2 cases. This capsule does not integrate the module or
adopt pending/wait mathematics, scoring, horizons or scientific stopping rules.
