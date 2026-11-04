# Local assignment, setup and reuse

The parent supplies the requested job, workspace, constraints, validated
endpoint and typed return form. The child chooses useful preparation, reuse,
diagnosis and execution actions within that assignment. These instructions are
supporting information; they are not a fixed action order or a complete episode.

The opt-in local practical binding requires an explicit configuration with
`kind=local`, an absolute `workspace` and a caller-owned resource `policy`.
The policy supplies `memory_bytes`, `scratch_bytes` and optional `wall_seconds`.
Use that actual policy and the assignment's `constraints`; this manual supplies
no allocation values or timeout and cannot change the selected limits.

The supplied inventory snapshot describes known preparations before the first
choice. Its canonical content hash and local/remote comparison identify catalog
bytes, not present runtime usability. Decide from the assigned software and
input requirements whether an existing executable, environment, database or
prepared wrapper needs checking. Reuse a valid setup. If something is missing
or incompatible, choose a scoped preparation/repair action and retain its
actual result. Do not silently substitute another database or algorithm.

Record executable/source/package and database identities at the specificity the
job needs. A file existing at an old path is weaker than a checked release/hash
or a successful relevant operation. Changes in load/free space/throughput are
current observations, separate from the reusable setup. Repairing one run's
conditions does not require rebuilding that setup or rewriting old records.

Native execution requires `systemd-run`, `systemctl`, a usable user systemd
manager and verified cgroup limits. Failure to establish that boundary returns
an operational failure; no unprotected fallback is installed. The native
lifecycle controls the process tree independently of the episode. Memory and
swap have cgroup limits; scratch is monitored with possible overshoot and a
per-file limit. This does not constitute a filesystem sandbox. Keep selected
files and generated control/output paths in the supplied workspace.
