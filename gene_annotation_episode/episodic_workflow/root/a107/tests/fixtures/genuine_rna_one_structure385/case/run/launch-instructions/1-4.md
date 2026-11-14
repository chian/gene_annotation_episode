# Existing detached phmmer local binding

Use this section when the caller binds the existing `ResourceEpisodes` local
homology resource or the original `HomologyEpisodes` job roles. That local
launch exposes `homology.*` tools. The other local sections describe the
separate opt-in practical binding's `practical.*` operations. These bindings
have distinct assignment formats and are not assembled or interchangeable
merely because this library documents both. Only the actual episode catalog
determines which operations can be selected.

The parent supplies an in-scope protein `query_ref`, CPU allocation and an
enabled search mode; the caller's registry fixes executable/database paths and
digests, maximum CPU and local limits. Ordering freezes the normalized query
FASTA, CPU and mode under the original operation/job identity. `native_defaults`
uses native heuristic filters; `maximum_sensitivity` adds `--max` only when
enabled and selected. It can cost more time and does not establish a function
or stronger significance. No timing transfer between modes is assumed.
An `existing_job_ref` repairs the same immutable job rather than changing its
query, CPU, mode, inputs or native reservation. Resource assignments additionally
retain exact resource selection, caller allocation and supplied input pins.

| Actual operation | Owning role and behavior |
| --- | --- |
| `homology.environment` | `launch_local` / original `job_launch`: inspect configured file presence, assigned CPU/mode, staging, intent and limits. |
| `homology.configure` | Same launch roles: check/apply the assigned CPU and pinned executable; empty arguments do not select a different CPU. |
| `homology.stage` | Same launch roles: prepare/repair private query/reference snapshots and reuse unchanged inputs; preserve the original database. |
| `homology.submit` | Same launch roles: validate pinned dependencies and submit the registered detached job once. Replay retains the original identity. |
| `homology.resume_start` | Same launch roles: reconcile the original prepared/submitting native reservation, without creating a replacement search. |
| `homology.check_handoff` | Same launch roles: open a fresh persistent receiver and check exact job/registry/interfaces, status, elapsed time and output availability. |
| `homology.sample` | Original `job_monitor`, not local launch: retain an actual selected status sample for an admitted handoff. |
| `homology.extract` | Resource `results` / original `job_results`: acquire a selected native-result page with explicit `limit`; use its `snapshot_ref` for later pages and explicit `retry_from` for a failed extraction attempt. |
| `homology.coverage` | Same results roles: read retained parsed/acquired coverage and parser/native completeness; no new poll or parsing. |
| `homology.errors` | Same results roles: read a selected page of recorded typed extraction failures. |

These are alternatives with factual prerequisites, not a mandatory sequence.
Inspect the returned state/failure before choosing any repair. A failed or
uncertain submission does not authorize another physical search. A usable
handoff is an operational receiving-interface result, not scientific completion.
The resource wrapper returns the original selected checked handoff and input
versions through the parent-defined form; closure does not invent a new poll.

Status includes native state/outcome, elapsed `systemd_service_wall_seconds`
and output availability/bytes, not search fraction or a stall judgment.
Inherited samples/checks remain prior information. The job can outlive a yielded
monitor; the episode/controller chooses further work without a prescribed
cadence, number of samples or timeout. Native `native.stdout`, `native.stderr`,
`hits.tbl` and `domains.tbl` belong to the original job/query/reference identity.
Retain valid partial extraction and distinguish it from complete acquisition.
Requested result references return through typed forms; the scientific parent
interprets matches and integrates annotation evidence. Source row L6 in
`docs/LAUNCH_INSTRUCTION_SOURCES_2026-10-22_001.md`.
